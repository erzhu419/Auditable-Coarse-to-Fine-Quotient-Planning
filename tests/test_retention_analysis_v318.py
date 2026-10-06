from copy import deepcopy
import pytest
from acfqp.science.retention_analysis_v318 import effects,summarize,VIEWS


def cohort():
    values=dict(FIRST=1.,R1_OWN_FULL=2.,R1_OWN_LOCAL=1.5,R2_OWN_FULL=3.,R2_OWN_LOCAL=4.,R2_FIRST_FULL=5.,R2_FIRST_LOCAL=8.)
    return [dict(lifecycle=life,parent=life%4,evaluations={view:dict(game_summaries=[
        dict(seed=317900000000+life*1000000+i,status='LOST',utility=values[view]) for i in range(32)])
        for view in VIEWS}) for life in range(16)]


def test_effects_keep_frozen_target_localization_and_interaction_signs_separate():
    result=summarize(cohort(),draws=32)
    assert {key:value['mean'] for key,value in result['effects'].items()}=={
        'TARGET_FIRST_FULL_MINUS_OWN_FULL':2.,'LOCAL_OWN_MINUS_FULL_OWN':1.,
        'TARGET_BY_LOCAL_INTERACTION':2.,'R1_LOCAL_MINUS_FULL':-.5}
    assert result['effects']['R1_LOCAL_MINUS_FULL']['status98_75']=='SUPPORTED_LOSS'
    assert result['mechanism_family']['interval_coverage']==.9875
    assert result['new_physical_evaluation_games']==2048
    assert result['secondary_own_first']['R2_FIRST_LOCAL']['mean']==7.


def test_no_lifecycle_or_seed_replacement_is_allowed():
    rows=cohort()
    with pytest.raises(ValueError,match='sixteen'):summarize(rows[:-1],draws=32)
    rows[0]['evaluations']['R1_OWN_LOCAL']['game_summaries'][0]['seed']+=1
    with pytest.raises(ValueError,match='paired'):summarize(rows,draws=32)


def test_one_counterfactual_cutoff_holds_every_mechanism_without_dropping_it():
    rows=cohort();rows[3]['evaluations']['R2_FIRST_LOCAL']['game_summaries'][0]['status']='CUTOFF'
    result=summarize(rows,draws=32)
    assert not result['complete_game_endpoints']
    assert len(result['cutoffs'])==1
    assert all(value['status98_75']=='HOLD_CUTOFF' for value in result['effects'].values())
    assert result['new_physical_evaluation_games']==2048


def test_bootstrap_reports_wider_family_interval_from_same_paired_distribution():
    rows=cohort()
    for row in rows:
        for game in row['evaluations']['R2_FIRST_FULL']['game_summaries']:game['utility']+=row['lifecycle']-8
    effect=summarize(rows,draws=400)['effects']['TARGET_FIRST_FULL_MINUS_OWN_FULL']
    assert effect['ci98_75'][0]<=effect['ci95'][0]<=effect['ci95'][1]<=effect['ci98_75'][1]
    assert len(effect['lifecycle_deltas'])==16
