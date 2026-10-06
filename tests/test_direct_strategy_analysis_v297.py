"""Complete-game science stays independent of direct-program search fitness."""
from copy import deepcopy

import pytest

from acfqp.science.direct_strategy_analysis_v297 import ARMS,PAIRS,PRIMARY,analyze,evaluation_seed


def science_games(life,value):
    return [dict(seed=evaluation_seed(life,i),utility=value,status='LOST',steps=10+i) for i in range(32)]


def cohort():
    rows=[]
    for life in range(16):
        references={}; rounds=[]
        for round_index in range(4):
            methods={}
            for method,sign in (('CEM',1.),('RANDOM_SEARCH',-1.)):
                candidates=[[sign*.1*i,0.,0.,0.] for i in range(8)]; ids=[]
                for i,theta in enumerate(candidates):
                    reference_id=f'L{life}-R{round_index}-{method if i else "ZERO"}-{i}'
                    references[reference_id]=dict(theta=theta,model_p_four=.12,environment_p_four=.1,
                        game_summaries=[dict(seed=297200010000+life*1000000+round_index*1000+replica,
                            utility=float(i),status='LOST',steps=20+replica) for replica in range(4)])
                    ids.append(reference_id)
                methods[method]=dict(candidates=candidates,reference_ids=ids,fitnesses=list(map(float,range(8))),
                                     winner_index=7,winner_theta=candidates[7])
            rounds.append(dict(round_index=round_index,arms=methods))
        arms={}
        for method,shift in zip(ARMS,(0.,2.,-1.)):
            theta=[0.]*4 if method=='SOURCE' else rounds[-1]['arms'][method]['winner_theta']
            arms[method]=dict(theta=theta,model_p_four=.12,environment_p_four=.1,
                game_summaries=science_games(life,life+5.+shift),
                training=dict(game_references=0 if method=='SOURCE' else 128,cutoff_games=0))
        rows.append(dict(lifecycle=life,parent=life%4,arms=arms,search_rounds=rounds,training_references=references))
    return rows


def choose_zero(row,method='CEM'):
    final=row['search_rounds'][-1]['arms'][method]
    for i,reference_id in enumerate(final['reference_ids']):
        for game in row['training_references'][reference_id]['game_summaries']: game['utility']=-float(i)
    final.update(fitnesses=[-float(i) for i in range(8)],winner_index=0,winner_theta=[0.]*4)
    row['arms'][method]['theta']=[0.]*4
    row['arms'][method]['game_summaries']=row['arms']['SOURCE']['game_summaries']


def test_primary_and_optimizer_contribution_use_independent_whole_game_science():
    result=analyze(cohort(),draws=20)
    assert result['primary_contrast']==PRIMARY
    assert set(result['paired_contrasts'])=={left+'_minus_'+right for left,right in PAIRS}
    assert result['paired_contrasts'][PRIMARY]['ci95']==[2.,2.]
    assert result['paired_contrasts']['CEM_minus_RANDOM_SEARCH']['mean']==3.
    assert result['paired_contrasts']['RANDOM_SEARCH_minus_SOURCE']['mean']==-1.
    assert result['stable_task_policy_gain_supported'] and result['optimizer_contribution_supported']
    assert result['arms']['CEM']['training_game_references']==16*128
    assert result['arms']['SOURCE']['training_game_references']==0
    assert result['physical_science_games']==result['logical_science_game_references']==16*3*32
    assert result['arms']['CEM']['games']==16*32
    assert 'No continuous strategic learning' in result['evidence_scope']


def test_training_winner_and_positive_secondary_cannot_override_negative_science():
    rows=cohort()
    for row in rows:
        for arm,shift in (('CEM',-1.),('RANDOM_SEARCH',-3.)):
            for game,source in zip(row['arms'][arm]['game_summaries'],row['arms']['SOURCE']['game_summaries']):
                game['utility']=source['utility']+shift
    result=analyze(rows,draws=20)
    assert result['paired_contrasts'][PRIMARY]['ci95']==[-1.,-1.]
    assert result['paired_contrasts'][PRIMARY]['improved_equal_worse']==[0,0,16]
    assert result['paired_contrasts'][PRIMARY]['adverse_lifecycles']==list(range(16))
    assert result['optimizer_contribution_supported'] and not result['stable_task_policy_gain_supported']
    assert all(r['arms']['CEM']['theta'][0]>0. for r in result['by_lifecycle'])


def test_exact_source_actor_sharing_keeps_zero_deltas_and_counts_physical_games_once():
    rows=cohort()
    for row in rows: choose_zero(row)
    result=analyze(rows,draws=20)
    assert result['paired_contrasts'][PRIMARY]['ci95']==[0.,0.]
    assert result['paired_contrasts'][PRIMARY]['improved_equal_worse']==[0,16,0]
    assert not result['stable_task_policy_gain_supported']
    assert result['physical_science_games']==16*2*32 and result['logical_science_game_references']==16*3*32
    assert all(r['unique_science_actors']==2 for r in result['by_lifecycle'])
    rows[0]['arms']['SOURCE']['game_summaries'][0]['status']='CUTOFF'
    cutoff=analyze(rows,draws=20)
    assert cutoff['physical_science_cutoffs']==1 and not cutoff['complete_natural_games']


def test_fixed_parent_whole_life_bootstrap_and_readonly_reproducibility():
    rows=cohort()
    for row in rows:
        for game,source in zip(row['arms']['CEM']['game_summaries'],row['arms']['SOURCE']['game_summaries']):
            game['utility']=source['utility']+row['parent']+1.
    before=deepcopy(rows); result=analyze(rows,draws=40)
    assert rows==before and result==analyze(list(reversed(rows)),draws=40)
    contrast=result['paired_contrasts'][PRIMARY]
    assert contrast['ci95']==[2.5,2.5] and contrast['parent_mean_deltas']=={str(p):p+1. for p in range(4)}
    assert result['bootstrap_seed']==29700001
    assert result['interval_scope']=='CONDITIONAL_ON_FOUR_FROZEN_PARENTS'
    assert result['estimator']=='EQUAL_SCIENCE_GAMES_THEN_LIFECYCLES'


@pytest.mark.parametrize('fault',['science_seed','training_fitness','science_reselection','candidate_budget','belief'])
def test_frozen_selection_pairing_and_search_inventory_mismatches_reject(fault):
    rows=cohort(); row=rows[0]
    if fault=='science_seed': row['arms']['CEM']['game_summaries'][0]['seed']=297200010000
    elif fault=='training_fitness': row['search_rounds'][3]['arms']['CEM']['fitnesses'][0]=999.
    elif fault=='science_reselection': row['arms']['CEM']['theta']=[.01,0.,0.,0.]
    elif fault=='candidate_budget': row['arms']['CEM']['training']['game_references']=124
    else: row['arms']['CEM']['model_p_four']=.1
    with pytest.raises(ValueError): analyze(rows,draws=20)


def test_actual_training_cutoff_reference_blocks_stable_task_confirmation():
    rows=cohort(); row=rows[0]
    reference_id=row['search_rounds'][0]['arms']['CEM']['reference_ids'][7]
    row['training_references'][reference_id]['game_summaries'][0]['status']='CUTOFF'
    row['arms']['CEM']['training']['cutoff_games']=1
    result=analyze(rows,draws=20)
    assert result['training_cutoff_references']==1 and result['physical_science_cutoffs']==0
    assert not result['complete_natural_games'] and not result['stable_task_policy_gain_supported']


def test_new_science_streams_are_disjoint_from_training_and_old_science():
    science={evaluation_seed(l,i) for l in range(16) for i in range(32)}
    training={297200010000+l*1000000+r*1000+i for l in range(16) for r in range(4) for i in range(4)}
    old={296600010000+l*1000000+p*100000+a*1000+i for l in range(16) for p in range(3) for a in range(3) for i in range(32)}
    assert len(science)==512 and min(science)==297900010000
    assert science.isdisjoint(training) and science.isdisjoint(old)
    assert 'raw tile' in analyze(cohort(),draws=20)['control_interpretation']
