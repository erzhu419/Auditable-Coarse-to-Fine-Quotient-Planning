"""Unknown predicate effects remain prior assignments, distinct from estimated zero."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path

import pytest

from scripts import analyze_controlled_predictive_supported_program_v164 as audit
from acfqp.science.controlled_predictive_supported_program_v164 import learn_programs
from acfqp.science.controlled_predictive_consequence_program_v163 import learn_programs as strict_learn

TEMP=Path(__file__).resolve().parents[1]/'reports/v164_runtime_tmp'
SYMBOLIC_WORK=Counter()


@pytest.fixture(scope='module',autouse=True)
def ledger(request):
    TEMP.mkdir(parents=True,exist_ok=True);before=request.session.testsfailed
    yield
    path=TEMP/'analyzer_checks.json';payload=json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    payload['attempts'].append(dict(tests=sum(item.module.__name__==__name__ for item in request.session.items),
        failures=request.session.testsfailed-before,new_environment_samples=0,weight_updates=0,
        symbolic_learning_counts=dict(SYMBOLIC_WORK),analysis_replay_work={},native_planner_calls=0,
        scope='Synthetic complete paid-pair vectors, prior/null distinction, support constraints and EVAL provenance use.'))
    path.write_text(json.dumps(payload,indent=2)+'\n')


def candidate():
    return dict(candidate_id='P0',first_action='LEFT',probe_action='DOWN',fixed_suffix=['RIGHT']*3,
        true_suffix=['DOWN']*3,false_suffix=['RIGHT']*3,occurrences=10,condition_counts={'true':5,'false':5})


def screening(false_seen=False,only_none=False):
    cells=[dict(heldout_life=0,query='risk1',candidates=[candidate()])]
    roots=[dict(root_id=f'{life}:{slot}',life=life,query='risk1') for life in range(4) for slot in range(4)]
    rows=[]
    for root in roots:
        for suffix in range(4):
            predicate=None if only_none or suffix==3 else False if false_seen and suffix==2 else True
            gains=(-4,4) if predicate is True else (0,0)
            for mode,gain in [('H2',0),('P0_A',gains[0]),('P0_B',gains[1])]:
                if root['life']==0 and mode!='H2':gain=999
                rows.append(dict(heldout_life=0,query='risk1',root_id=root['root_id'],suffix=suffix,mode=mode,
                    status='LOST',components=[11+gain,1.,0.],utility=10+gain,module={'predicate':predicate}))
    return cells,roots,rows


def checked_learn(cells,roots,rows):
    result=learn_programs(cells,roots,rows);SYMBOLIC_WORK.update(sum((Counter(c['learning_counts']) for c in result),Counter()))
    independent=audit.independent_selection(cells,roots,list(reversed(rows)))
    assert audit.mobility.arithmetic.equivalent(result,independent)
    return independent[0]


def test_unsupported_leaf_retains_source_and_unknown_delta():
    cells,roots,rows=screening();cell=checked_learn(cells,roots,rows);score=cell['candidate_scores'][0]
    assert cell['complete'] and not cell['all_predicates_identified'] and not cell['selected_program_all_predicates_identified']
    assert score['condition_counts']=={'true':36,'false':0,'none':12}
    evidence=score['predicate_evidence']
    assert evidence['true']==dict(support=36,provenance='terminal_estimated',component_delta_A_minus_B=[-6.,0.,0.],
        utility_delta_A_minus_B=-6.,prior_assignment='A',allowed_assignments=['A','B'])
    assert evidence['false']==dict(support=0,provenance='source_prior',component_delta_A_minus_B=None,
        utility_delta_A_minus_B=None,prior_assignment='B',allowed_assignments=['B'])
    assert score['allowed_mapping_codes']==['AB','BB'] and score['learned_mapping']=='BB'
    assert cell['programs']['LEARNED']['mapping']=={'true':'B','false':'B'}
    assert cell['learning_counts']['terminal_supported_assignments']==1 and cell['learning_counts']['retained_source_assignments']==1
    assert cell['learning_counts']['evidence_vector_selections']==48
    assert not strict_learn(cells,roots,rows)[0]['complete']


def test_estimated_zero_leaf_is_identified_and_can_change_assignment():
    cells,roots,rows=screening(false_seen=True);cell=checked_learn(cells,roots,rows);score=cell['candidate_scores'][0]
    assert cell['complete'] and cell['all_predicates_identified'] and cell['selected_program_all_predicates_identified']
    evidence=score['predicate_evidence']['false']
    assert evidence['support']==12 and evidence['provenance']=='terminal_estimated'
    assert evidence['component_delta_A_minus_B']==[0.,0.,0.] and evidence['utility_delta_A_minus_B']==0.
    assert evidence['allowed_assignments']==['A','B'] and score['allowed_mapping_codes']==['AA','AB','BA','BB']
    assert score['learned_mapping']=='BA'
    strict=strict_learn(cells,roots,rows)[0]
    assert cell['programs']==strict['programs']
    assert score['mapping_scores']==strict['candidate_scores'][0]['mapping_scores']


def test_no_predicates_observed_keeps_entire_prior_map_and_global_ablation():
    cells,roots,rows=screening(only_none=True)
    for row in rows:
        if row['mode']!='H2':row.update(components=[10.,1.,0.],utility=9.)
    cell=checked_learn(cells,roots,rows);score=cell['candidate_scores'][0]
    assert cell['complete'] and not cell['all_predicates_identified']
    assert score['allowed_mapping_codes']==['AB'] and score['learned_mapping']=='AB' and score['global_mapping']=='AA'
    assert score['condition_counts']=={'true':0,'false':0,'none':48}
    assert cell['programs']['LEARNED']['train_gain']==-1.
    assert all(e['component_delta_A_minus_B'] is None for e in score['predicate_evidence'].values())
    assert cell['learning_counts']['retained_source_assignments']==2 and cell['learning_counts']['terminal_supported_assignments']==0


@pytest.mark.parametrize('corruption,issue',[('cutoff','nonterminal_pair'),('predicate','predicate_mismatch'),('none_vector','none_outcome_mismatch')])
def test_incomplete_pair_still_blocks_evaluation(corruption,issue):
    cells,roots,rows=screening();bad=next(r for r in rows if r['root_id']=='1:0' and r['mode']=='P0_B' and r['suffix']==3)
    if corruption=='cutoff':bad.update(status='CUTOFF',utility=None)
    elif corruption=='predicate':bad['module']['predicate']=False
    else:bad.update(components=[99.,1.,0.],utility=98.)
    cell=checked_learn(cells,roots,rows);score=cell['candidate_scores'][0]
    assert not cell['complete'] and cell['programs']=={} and not cell['selected_program_all_predicates_identified']
    assert issue in score['issues'] and score['allowed_mapping_codes']==[] and score['mapping_scores']==[]
    assert score['predicate_evidence']['true']['provenance']=='terminal_incomplete'
    assert score['predicate_evidence']['true']['component_delta_A_minus_B'] is None
    assert score['predicate_evidence']['false']['provenance']=='source_prior'
    assert score['predicate_evidence']['false']['allowed_assignments']==[]


def evaluation(programs):
    roots=[dict(root_id=f'{life}:0',life=life,query='risk1',replica=0,slot=0) for life in range(4)]
    rows=[]
    for root in roots:
        for suffix in range(16):
            predicate=True if suffix<4 else False if suffix<8 else None
            for mode in audit.MODES:
                gain=suffix+root['life'] if mode=='LEARNED' else 2 if mode=='MODAL' else 0
                rows.append(dict(root_id=root['root_id'],suffix=suffix,mode=mode,status='LOST',utility=10+gain,
                    components=[11+gain,1.,0.],module=dict(program=candidate() if mode!='H2' else None,
                    predicate=predicate if mode not in ('H2','FIXED') else None,
                    prefix_steps=0 if mode=='H2' else 4,attempts=0 if mode=='H2' else 4,
                    exit_reason='baseline' if mode=='H2' else 'budget')))
    return roots,rows


def test_actual_eval_prior_usage_is_counted_without_filtering_utility_cohort():
    cells,train_roots,train_rows=screening();frozen=checked_learn(cells,train_roots,train_rows)
    programs=[dict(deepcopy(frozen),heldout_life=life) for life in range(4)]
    roots,rows=evaluation(programs);summary=audit.summarize_eval(roots,rows,programs)
    diagnostic=next(d for d in summary['learned_provenance_diagnostics'] if d['query']=='risk1')
    assert diagnostic['complete'] and diagnostic['branches']==64
    assert diagnostic['branch_counts']=={'terminal_supported':16,'source_prior':16,'none':32}
    assert all(h['branch_counts']=={'terminal_supported':4,'source_prior':4,'none':8} for h in diagnostic['per_history'])
    assert not any(h['selected_program_all_predicates_identified'] for h in diagnostic['per_history'])
    comparison=next(c for c in summary['comparisons'] if c['query']=='risk1' and c['contrast']=='LEARNED-MODAL')
    assert comparison['complete'] and comparison['roots']==4 and comparison['metrics']['utility']['mean']==7.
    # A prior branch remains part of the primary estimate, including its cutoff.
    bad=next(r for r in rows if r['mode']=='LEARNED' and r['module']['predicate'] is False)
    bad.update(status='CUTOFF',utility=None)
    incomplete=audit.summarize_eval(roots,rows,programs)
    comparison=next(c for c in incomplete['comparisons'] if c['query']=='risk1' and c['contrast']=='LEARNED-MODAL')
    assert not comparison['complete'] and comparison['metrics']['utility']['mean'] is None
