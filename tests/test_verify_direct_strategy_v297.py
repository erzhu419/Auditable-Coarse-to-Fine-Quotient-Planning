"""Finite mutations of retained program search/costs; no new environment calls."""
from copy import deepcopy
import json
from pathlib import Path
from statistics import mean
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import verify_direct_strategy_v297 as audit


@pytest.fixture(scope='module')
def retained():
    return json.loads((ROOT/'reports/direct_strategy_v297/summary.json').read_text())


def test_training_fitness_cannot_be_replaced_by_science_performance(retained):
    life=deepcopy(retained['by_lifecycle'][0])
    life['search_rounds'][0]['arms']['CEM']['fitnesses'][1]+=1
    with pytest.raises(ValueError,match='training utility alone'):
        audit.reconstruct_search(life)


@pytest.mark.parametrize('field',['mean_after','sigma_after'])
def test_cem_distribution_update_is_reconstructed_from_top_two(retained,field):
    life=deepcopy(retained['by_lifecycle'][0])
    life['search_rounds'][0]['arms']['CEM'][field][0]+=.01
    with pytest.raises(ValueError,match='literal top-two/population-spread update'):
        audit.reconstruct_search(life)


def test_same_program_has_one_physical_training_batch(retained):
    life=deepcopy(retained['by_lifecycle'][0])
    key=next(iter(life['training_references']))
    life['training_references']['duplicate']=deepcopy(life['training_references'][key])
    with pytest.raises(ValueError,match='every physical training batch is used once'):
        audit.reconstruct_search(life)


def test_science_actor_must_be_the_frozen_final_round_winner(retained):
    life=deepcopy(next(l for l in retained['by_lifecycle'] if l['arms']['CEM']['theta']!=audit.ZERO))
    life['arms']['CEM']['theta']=list(audit.ZERO)
    with pytest.raises(ValueError,match='science must use final round-four actor'):
        audit.check_lifecycle(life,life['model_p_four'])


@pytest.mark.parametrize('field',['raw_tile_productions','environment_random_draws'])
def test_actual_initial_spawns_and_random_draws_are_paid(retained,field):
    life=retained['by_lifecycle'][0]
    batch=deepcopy(life['arms']['SOURCE'])
    batch['counts']['environment'][field]-=2 if field=='raw_tile_productions' else 4
    with pytest.raises(ValueError,match='all physical complete-game raw costs'):
        audit.check_batch(batch,[audit.science_seed(0,i) for i in range(32)],life['model_p_four'],audit.ZERO)


def test_signed_summary_keeps_all_adverse_lifecycles(retained):
    summary=deepcopy(retained['summary'])
    summary['paired_contrasts']['CEM_minus_SOURCE']['adverse_lifecycles'].pop()
    with pytest.raises(ValueError,match='all utility adverse lives retained'):
        audit.check_summary(summary,summary['by_lifecycle'])


def contrast(values):
    center=mean(values)
    return dict(mean=center,ci95=[center,center],
        lifecycle_deltas={str(i):v for i,v in enumerate(values)},
        parent_mean_deltas={str(p):mean(values[p::4]) for p in range(4)},
        improved_equal_worse=[sum(v>0 for v in values),sum(v==0 for v in values),sum(v<0 for v in values)],
        adverse_lifecycles=[i for i,v in enumerate(values) if v<0],
        interval_scope='CONDITIONAL_ON_FOUR_FROZEN_PARENTS')


def test_shared_zero_actor_cutoff_counts_once_per_physical_batch():
    """A supported max_steps cutoff shared by SOURCE/CEM is one physical result."""
    records=[]
    for life in range(16):
        arms={}
        for method in audit.ARMS:
            shared=method!='RANDOM_SEARCH'
            arms[method]=dict(games=32,mean_game_utility=0. if shared else 1.,wins=0,
                losses=31 if shared else 32,cutoffs=1 if shared else 0,steps=320,
                theta=list(audit.ZERO) if shared else [.5]*4,model_p_four=.105,
                training_game_references=0 if method=='SOURCE' else 128,training_cutoff_references=0)
        records.append(dict(lifecycle=life,parent=life%4,arms=arms,
            unique_science_actors=2,physical_science_games=64,logical_science_game_references=96))
    summary=dict(by_lifecycle=records,arms={},paired_contrasts={},complete_natural_games=False,
        training_cutoff_references=0,physical_science_cutoffs=16,physical_science_games=1024,
        logical_science_game_references=1536,training_game_references_per_search_arm=2048,
        stable_task_policy_gain_supported=False,optimizer_contribution_supported=False,
        primary_contrast='CEM_minus_SOURCE',bootstrap_seed=29700001,bootstrap_draws=20000,
        interval_scope='CONDITIONAL_ON_FOUR_FROZEN_PARENTS',estimator='EQUAL_SCIENCE_GAMES_THEN_LIFECYCLES')
    for method in audit.ARMS:
        summary['arms'][method]=dict(mean_game_utility=mean(r['arms'][method]['mean_game_utility'] for r in records),
            **{k:sum(r['arms'][method][k] for r in records) for k in ('games','wins','losses','cutoffs','steps',
                'training_game_references','training_cutoff_references')})
    for left,right in audit.PAIRS:
        summary['paired_contrasts'][left+'_minus_'+right]=contrast(
            [r['arms'][left]['mean_game_utility']-r['arms'][right]['mean_game_utility'] for r in records])
    audit.check_summary(summary,records)
    summary['physical_science_cutoffs']=32
    with pytest.raises(ValueError,match='physical shared evaluations'):
        audit.check_summary(summary,records)
