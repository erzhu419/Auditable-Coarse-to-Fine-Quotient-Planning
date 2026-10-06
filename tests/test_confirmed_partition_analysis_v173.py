"""Independent centered proposal, fixed-node confirmation and source-cluster gates."""
from copy import deepcopy
from collections import Counter

import pytest

from scripts import analyze_controlled_predictive_confirmed_partition_v173 as audit
from scripts import run_controlled_predictive_confirmed_partition_v173 as runner
from acfqp.science import controlled_predictive_confirmed_partition_v173 as core
from acfqp.science import controlled_predictive_consequence_partition_v172 as learner
from test_confirmed_partition_core_v173 import proposal,roots_pair,confirm_root,outcomes,true_vectors

ROWS = []


def examples():
    rows = []
    for index in range(16):
        side = int(index>=8); board = [side]+[0]*14+[2]; preferred = 'LEFT' if not side else 'DOWN'
        rows.append(dict(root_id=f'discovery:{index}',life=0,source_id=f'discovery_source:{index//4}',canonical_board=board,
            legal_actions=['DOWN','LEFT'],immediate_rewards={'DOWN':0.,'LEFT':0.},
            suffix_trials=[dict(suffix=suffix,seed=100*index+suffix,action_components={action:[4.,0.,1.] if action==preferred else [0.,1.,0.] for action in ('DOWN','LEFT')}) for suffix in range(4)]))
    return rows


def test_independent_discovery_node_fits_account_explicit_centered_constraints():
    rows = examples(); actual,expected = core.propose_partition(rows,0),audit.independent_proposal(rows,0)
    assert audit._equal(actual,expected)
    assert expected['fit_counts']['zero_sum_constraint_rows']==9
    assert expected['node_fit_counts']['zero_sum_constraint_rows']==3
    assert expected['fit_counts']['centered_solver_matrix_cells']==3*28
    for mode in ('ONE_LATE','COARSE_LATE'):
        expected_control = audit.independent_partition(rows,0,mode)
        assert audit._equal(learner.fit_partition(rows,0,mode),expected_control)
        assert expected_control['fit_counts']['zero_sum_constraint_cells']==12
    empty = Counter(); audit.independent_leaf_fit([dict(rows[0],legal_actions=['DOWN'],suffix_trials=[dict(suffix=0,seed=1,action_components={'DOWN':[1.,0.,1.]})])],empty)
    assert empty.get('zero_sum_constraint_rows',0)==0


def test_independent_node_choice_route_and_direct_child_work_before_any_labels():
    model = proposal(deeper=True); roots = list(reversed(roots_pair()))
    actual,work = core.freeze_node_choices({0:model},roots)
    independent,expected_work = audit.freeze_node_choices({0:model},roots)
    assert audit._equal(actual,independent) and work==expected_work
    assert independent[0]['node_id']==0 and independent[0]['child_node_id']==1
    assert independent[0]['child_action']=='LEFT'
    assert learner.choose_action(model,roots[-1])['canonical_action']=='DOWN'
    assert expected_work['proposal_node_lookups']>expected_work['proposal_feature_threshold_tests']


@pytest.mark.parametrize('scenario',['retained','noise','ancestor','sparse','unsupported'])
def test_independent_full_vector_cluster_statistics_and_topdown_pruning(scenario):
    model,roots = proposal(scenario in ('ancestor','sparse')),roots_pair()
    vectors = true_vectors
    if scenario=='noise': vectors = lambda root,suffix,action:[4. if action=='DOWN' else 8.*(suffix%2==0),1.,0.]
    elif scenario=='ancestor':
        roots = [confirm_root(source,index,side,subside) for source in range(8) for index,side,subside in ((0,0,0),(1,0,1),(2,1,0))]
        vectors = lambda root,suffix,action:[2.*(action=='DOWN'),1.,0.]
    elif scenario=='sparse':
        roots = [confirm_root(source,2,1,0) for source in range(8)]+[confirm_root(source,index,0,index) for source in range(2) for index in (0,1)]
        vectors = lambda root,suffix,action:[4.*(action=='DOWN'),1.,0.]
    frozen,_ = audit.freeze_node_choices({0:model},roots)
    if scenario=='unsupported':
        for row in frozen:
            if row['source_id'] not in ('confirm_source:0','confirm_source:1'): row['child_decision']['support']['complete']=False
    values = outcomes(roots,vectors); candidates = 32
    actual,record = core.confirm_and_prune(model,roots,frozen,values,candidates)
    independent,expected = audit.confirm_and_prune(model,roots,frozen,values,candidates)
    assert audit._equal(actual,independent) and audit._equal(record,expected)
    assert independent['node_fits']==model['node_fits'] and independent['fit_counts']==model['fit_counts']
    if scenario=='ancestor':
        assert expected['nodes'][1]['local_pass'] and not expected['nodes'][1]['reachable']
        assert independent['leaves']==[model['node_fits']['0']]
    elif scenario=='sparse':
        clusters = expected['nodes'][1]['clusters']; assert len(clusters)==8
        assert sum(row['in_region_roots']==0 for row in clusters)==6
        assert clusters[0]['utility']==pytest.approx(4./3.)
    elif scenario=='unsupported':
        assert expected['nodes'][0]['eligible'] and not expected['nodes'][0]['all_region_supported']
        assert expected['nodes'][0]['metrics']['utility']['mean']==2.


@pytest.mark.parametrize('fault',['missing','duplicate','cutoff','seed','component'])
def test_incomplete_or_misbound_confirm_vectors_stop_before_any_pruned_policy(fault):
    model,roots = proposal(),roots_pair(); values = outcomes(roots,true_vectors)
    if fault=='missing': values.pop()
    elif fault=='duplicate': values.append(deepcopy(values[0]))
    elif fault=='cutoff': values[0].update(status='CUTOFF',utility=None)
    elif fault=='seed': values[0]['seed']+=900
    else: values[0]['components'][2]=1.-values[0]['components'][2]
    frozen,_ = audit.freeze_node_choices({0:model},roots)
    actual,record = core.confirm_and_prune(model,roots,frozen,values,1)
    independent,expected = audit.confirm_and_prune(model,roots,frozen,values,1)
    assert actual is independent is None and audit._equal(record,expected) and not expected['complete']


def test_family_size_uses_all_frozen_candidates_including_rejected_descendants():
    model,roots = proposal(),roots_pair(); frozen,_ = audit.freeze_node_choices({0:model},roots)
    values = outcomes(roots,lambda root,suffix,action:[4.+4.*(int(root['source_id'].split(':')[-1])>=4) if action=='LEFT' else 4.,1.,0.])
    _,small = audit.confirm_and_prune(model,roots,frozen,values,1); _,large = audit.confirm_and_prune(model,roots,frozen,values,32)
    assert small['nodes'][0]['local_pass'] and not large['nodes'][0]['local_pass']
    assert large['family']['z']>small['family']['z']


def validation_fixture():
    roots = []
    for life in range(4):
        for replica in range(8):
            for slot in range(1 if replica==0 else 2):
                source=f'VALID_SOURCE:{life}:risk1:{replica}'
                roots.append(dict(root_id=f'{source}:{slot}',life=life,query='risk1',replica=replica,slot=slot,source_id=source,
                    canonical_board=[1]+[0]*15,legal_actions=['DOWN','LEFT'],immediate_rewards={'DOWN':0.,'LEFT':0.},teacher_action='LEFT',
                    actions=[dict(canonical_action=a,actual_action=a) for a in ('DOWN','LEFT')]))
    plans = audit.forced_roster(roots,'VALID')
    values = [dict(plan,score=2048*float(plan['replica'])*(plan['canonical_action']=='DOWN'),steps=1,status='WON',
        components=[float(plan['replica'])*(plan['canonical_action']=='DOWN'),0.,1.],utility=float(plan['replica'])*(plan['canonical_action']=='DOWN')+1.) for plan in plans]
    choices = [dict(root_id=root['root_id'],life=root['life'],source_id=root['source_id'],mode=mode,canonical_action='DOWN' if mode=='PART_CONFIRMED' else 'LEFT',
        actual_action='DOWN' if mode=='PART_CONFIRMED' else 'LEFT',fallback=False,decision=dict(support=dict(complete=False),predicted_pairs={})) for root in roots for mode in (*audit.MODES,'H2')]
    return roots,values,choices


def test_final_source_pool_ci_requires_fresh_validation_and_retained_structure():
    roots,values,choices = validation_fixture()
    expected = audit.summarize(values,roots,choices,1)
    assert audit._equal(runner.summarize(values,roots,choices,1),expected)
    stat = expected['comparisons'][0]['metrics']['utility']
    assert stat['mean']==3.5 and stat['mean_variance']==pytest.approx(.1875)
    assert expected['progression']['status']=='PASS'
    collapsed = audit.summarize(values,roots,choices,0)
    assert collapsed['progression']['status']=='FAIL' and not collapsed['progression']['structure_eligible']
    values.pop(); assert audit.summarize(values,roots,choices,1)['progression']['status']=='HOLD'


def test_phase_seed_layout_and_exclusion_do_not_replace_paid_source_roots():
    roots,_,_ = validation_fixture()
    for phase in ('CONFIRM','VALID'): assert audit.forced_roster(roots,phase)==runner.branch_roster(roots,phase)
    for phase in ('CONFIRM_SOURCE','VALID_SOURCE'): assert audit.source_roster(phase)==runner.source_roster(phase)
    assert audit.seed('CONFIRM',0,1,2,3)!=audit.seed('VALID',0,1,2,3)
    candidates = deepcopy(roots); seen = [candidates[0]]
    fresh = audit.fresh_roots(candidates,seen,'VALID')
    assert fresh==runner.fresh_roots(candidates,seen,'VALID') and not fresh['roots']
    assert len(fresh['excluded'])==len(candidates) and ROWS==[]
