"""Independent full-vector fit, source-cluster uncertainty and frozen cohorts."""
from collections import Counter
from copy import deepcopy
import json

import pytest

from scripts import analyze_controlled_predictive_consequence_partition_v172 as audit
from scripts import run_controlled_predictive_consequence_partition_v172 as runner
from acfqp.science import controlled_predictive_consequence_partition_v172 as core

ROWS = []  # All fixtures below are deterministic: no new environment acquisitions.


def example(index,board_value=1,positive=True,legal=('DOWN','LEFT'),life=0):
    vectors = {'DOWN':[4.,0.,1.],'LEFT':[0.,1.,0.],'RIGHT':[2.,1.,0.],'UP':[1.,0.,1.]}
    if not positive: vectors['DOWN'],vectors['LEFT'] = vectors['LEFT'],vectors['DOWN']
    return dict(root_id=f'root:{index:03}',source_id=f'source:{index%4}',life=life,canonical_board=[board_value]*2+[0]*14,
        legal_actions=list(legal),immediate_rewards={action:float(action=='DOWN') for action in legal},
        suffix_trials=[dict(suffix=suffix,seed=100+suffix,action_components={action:list(vectors[action]) for action in legal}) for suffix in range(4)])


def decision_root(ex,teacher='DOWN'):
    return {key:deepcopy(ex[key]) for key in ('life','canonical_board','legal_actions','immediate_rewards')} | dict(teacher_action=teacher)


@pytest.mark.parametrize('mode',audit.MODES)
def test_independent_centered_full_vector_math_tree_and_actual_fit_work(mode):
    examples = [example(i,1 if i<16 else 7,i<16) for i in range(32)]+[example(99,life=1)]
    actual = core.fit_partition(examples,0,mode); independent = audit.independent_partition(examples,0,mode)
    assert audit._equal(actual,independent)
    assert independent['fit_counts']['other_life_examples_excluded']==1
    for leaf in independent['leaves']:
        for group in leaf['connected_components']:
            assert [sum(leaf['coefficients'][action][k] for action in group) for k in range(3)]==pytest.approx([0.,0.,0.])
    if mode.startswith('PART_'):
        assert independent['nodes'][0]['cell']==0 and independent['nodes'][0]['threshold']==1
        assert len(independent['leaves'])==2 and all(leaf['loss']==pytest.approx(0.) for leaf in independent['leaves'])


def test_equal_root_pair_mass_disconnected_gauges_and_singleton_action_support():
    two,four,single = example(0),example(1,legal=audit.ACTIONS),example(2,legal=('UP',))
    assert sum(sample[2] for sample in audit.pair_samples(two))==pytest.approx(1.)
    assert sum(sample[2] for sample in audit.pair_samples(four))==pytest.approx(1.)
    assert audit.pair_samples(single)==[]
    examples = [two,single]; result = audit.independent_partition(examples,0,'ONE_LATE')
    assert audit._equal(core.fit_partition(examples,0,'ONE_LATE'),result)
    leaf = result['leaves'][0]
    assert leaf['connected_components']==[['DOWN','LEFT'],['RIGHT'],['UP']]
    assert leaf['action_root_ids']['UP']==['root:002'] and leaf['coefficients']['UP']==[0.,0.,0.]


def test_frozen_choices_use_all_components_known_reward_and_same_support_fallback():
    examples = [example(i) for i in range(4)]
    for ex in examples:
        for trial in ex['suffix_trials']: trial['action_components'].update(DOWN=[4.,1.,0.],LEFT=[3.,0.,1.])
    payload = audit.independent_partition(examples,0,'ONE_LATE'); root = decision_root(examples[0])
    assert audit._equal(core.choose_action(payload,root),audit.independent_choice(payload,root))
    assert audit.independent_choice(payload,root)['canonical_action']=='LEFT'
    root['immediate_rewards']['DOWN']=4.
    assert audit.independent_choice(payload,root)['canonical_action']=='DOWN'
    root.update(legal_actions=['DOWN','RIGHT'],immediate_rewards={'DOWN':4.,'RIGHT':0.})
    assert audit.independent_choice(payload,root)['reason']=='insufficient_action_support'
    root.update(legal_actions=['RIGHT'],teacher_action='RIGHT')
    assert audit.independent_choice(payload,root)['reason']=='single_legal_action'
    assert audit._equal(core.choose_action(payload,root),audit.independent_choice(payload,root))


def test_split_requires_two_distinct_source_games_in_each_child():
    examples = [example(i,1 if i<8 else 7,i<8) for i in range(16)]
    for i,ex in enumerate(examples): ex['source_id']='only_left' if i<8 else f'right:{i%2}'
    independent = audit.independent_partition(examples,0,'PART_LATE')
    assert audit._equal(core.fit_partition(examples,0,'PART_LATE'),independent)
    assert len(independent['leaves'])==1 and independent['fit_counts'].get('supported_split_candidates',0)==0


def roots_and_outcomes():
    roots = []
    for life in range(4):
        for replica in range(8):
            # Unequal root counts must not reweight independently acquired games.
            for slot in range(1 if replica==0 else 2):
                source_id=f'VALID_SOURCE:{life}:risk1:{replica}'
                roots.append(dict(root_id=f'{source_id}:{slot}',life=life,query='risk1',replica=replica,slot=slot,source_id=source_id,
                    canonical_board=[1,0,1]+[0]*13,legal_actions=['DOWN','LEFT'],immediate_rewards={'DOWN':0.,'LEFT':0.},teacher_action='LEFT',
                    actions=[dict(canonical_action=action,actual_action=action) for action in ('DOWN','LEFT')]))
    plans = audit.forced_roster(roots,'VALID')
    outcomes = []
    for plan in plans:
        reward = float(plan['replica']) if plan['canonical_action']=='DOWN' else 0.
        outcomes.append(dict(plan,score=reward*2048,steps=1,status='WON',components=[reward,0.,1.],utility=reward+1.))
    choices = [dict(root_id=root['root_id'],life=root['life'],source_id=root['source_id'],mode=mode,
        canonical_action='DOWN' if mode=='PART_LATE' else 'LEFT',actual_action='DOWN' if mode=='PART_LATE' else 'LEFT',fallback=False,
        decision=dict(support=dict(complete=False),predicted_pairs={})) for root in roots for mode in (*audit.MODES,'H2')]
    return roots,plans,outcomes,choices


def test_independent_source_cluster_ci_equal_weights_and_two_primary_progression():
    roots,_,outcomes,choices = roots_and_outcomes()
    actual,independent = runner.summarize(outcomes,roots,choices),audit.summarize(outcomes,roots,choices)
    assert audit._equal(actual,independent)
    stats = independent['comparisons'][0]['metrics']['utility']
    assert stats['mean']==pytest.approx(3.5) and stats['mean_variance']==pytest.approx(.1875)
    assert independent['progression']['status']=='PASS' and independent['progression']['passed']==2
    assert all(history['source_clusters']==8 for history in independent['comparisons'][0]['per_history'])
    assert 'conditional_source_ci95' in stats and 'conditional_suffix_ci95' not in stats


@pytest.mark.parametrize('failure',['missing','duplicate','cutoff','wrong_success'])
def test_incomplete_full_vector_pair_is_retained_as_hold_and_never_replaced(failure):
    roots,plans,outcomes,choices = roots_and_outcomes()
    if failure=='missing': outcomes.pop()
    elif failure=='duplicate': outcomes.append(deepcopy(outcomes[-1]))
    elif failure=='cutoff': outcomes[-1].update(status='CUTOFF',utility=None)
    else: outcomes[-1]['components'][2]=0.
    assert not audit.assemble_examples(roots,plans,outcomes)['complete']
    summary = audit.summarize(outcomes,roots,choices)
    assert audit._equal(runner.summarize(outcomes,roots,choices),summary)
    assert summary['progression']['status']=='HOLD' and all(row['metrics']['utility']['mean'] is None for row in summary['comparisons'])


def test_validation_exact_canonical_exclusion_has_no_replacement():
    train = [dict(canonical_board=[1]+[0]*15)]
    candidates = [dict(root_id='seen',canonical_board=[1]+[0]*15),dict(root_id='new',canonical_board=[2]+[0]*15)]
    fresh,excluded = audit.validation_freshness(candidates,train)
    assert [row['root_id'] for row in fresh]==['new'] and [row['root_id'] for row in excluded]==['seen']
    assert len(fresh)+len(excluded)==len(candidates)


def test_middle_quantiles_transport_original_source_action_and_keep_reward_parameter():
    source = dict(source_id='TRAIN_SOURCE:0:risk1:3',phase='TRAIN_SOURCE',life=0,query='risk1',replica=3,
        seed=audit.seed('TRAIN_SOURCE',0,3),result=dict(status='WON'),actions=['DOWN']*18,
        choices=[dict(afterstate=[1+step%5]+[0]*15) for step in range(18)],spawned_cells=[15]*18,spawned_ranks=[1]*18)
    roots = audit.source_roots(source)
    assert roots==runner.roots_from_source(source)
    assert [root['source_step'] for root in roots]==list(range(2,18,2))
    assert all(root['teacher_action'] in root['legal_actions'] for root in roots)
    assert all(root['generation_counts']['action_transports']==len(root['actions'])+1 for root in roots)
    assert audit.source_roster('TRAIN_SOURCE')==runner.source_roster('TRAIN_SOURCE')
    assert audit.forced_roster(roots,'TRAIN')==runner.branch_roster(roots,'TRAIN')


def test_new_physical_source_and_forced_trace_delegate_once_without_old_raw_replay(monkeypatch,tmp_path):
    calls = []; fake = dict(branch_id='TRAIN:root:0:DOWN',phase='TRAIN',root_id='root',life=0,query='risk1',replica=0,slot=0,suffix=0,
        seed=audit.seed('TRAIN',0,0),canonical_action='DOWN',actual_action='DOWN',root_board=[0]*16,first_action='DOWN',module={},
        result=dict(score=0,steps=1,status='WON',components=[0.,0.,1.],utility=1.,environment_counts={'sampled_transitions':1},policy_counts={},
            program_setup_counts={},learning_counts={},policy_counts_by_query={'risk1':{},'risk8':{}},decision_seconds=0.,seconds=0.))
    plan = {key:fake[key] for key in ('branch_id','phase','root_id','life','query','replica','slot','suffix','seed','canonical_action','actual_action')}
    compact = dict(plan,score=0,steps=1,status='WON',components=[0.,0.,1.],utility=1.,module={})
    (tmp_path/'outcomes.json').write_text(json.dumps([compact]))
    lifecycle = dict(life=0,outcomes_ref='outcomes.json',branch_trace='new_trace.gz',physical_branches=1,environment_counts={'sampled_transitions':1},
        policy_counts={},program_setup_counts={},statuses={'WON':1})
    monkeypatch.setattr(audit.prior.prior.old,'read_rows',lambda path:iter([deepcopy(fake)]))
    monkeypatch.setattr(audit.previous,'replay_forced',lambda row:(calls.append(('forced',row['branch_id'])) or {'ground':True},3))
    monkeypatch.setattr(audit.previous,'replay_eval',lambda *args:pytest.fail('forced row reached SOURCE replay'))
    monkeypatch.setattr(audit.prior,'teacher_checks',lambda *args:{'teacher':True})
    result = audit.replay_lifecycle((str(tmp_path),'TRAIN',lifecycle,{},[plan],[dict(root_id='root',board=[0]*16)]))
    assert all(result['checks'].values()) and calls==[('forced',plan['branch_id'])]
    assert result['costs']['physical_branches']==1 and ROWS==[]
