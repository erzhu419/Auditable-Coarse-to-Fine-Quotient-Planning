"""Finite receipt mutations for stable B; no new games or bootstrap draws."""
from copy import deepcopy
import gzip
import json
from pathlib import Path
from statistics import mean
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import verify_stable_b_v298 as audit


@pytest.fixture(scope='module')
def retained():
    """Only existing V291 receipt shapes; these fixtures are not V298 evidence."""
    return json.loads((ROOT/'reports/independent_episode_v291/summary.json').read_text())


@pytest.mark.parametrize('phase,p', [('A', .5), ('B', .1)])
def test_actual_environment_must_be_stable_b(phase, p):
    audit.check_b_context(dict(phase='B', true_p_four=.5))
    with pytest.raises(ValueError, match='stable B actual environment'):
        audit.check_b_context(dict(phase=phase, true_p_four=p))


def test_warmup_cannot_reuse_old_a_seed_family(retained):
    with gzip.open(retained['parent_receipts'][0]['trace_file'], 'rt') as stream:
        row = json.loads(next(stream))
    row.update(phase='B', true_p_four=.5)
    old_seed = row['summary']['seed']
    row['summary']['seed'] = audit.warmup_seed(0, 0)
    audit.check_warmup(row, 0, audit.Memory())
    row['summary']['seed'] = old_seed
    with pytest.raises(ValueError, match='fresh complete warmup seed'):
        audit.check_warmup(row, 0, audit.Memory())


def test_evaluation_cannot_reuse_old_a_histories(retained):
    arm = retained['by_lifecycle'][0]['arms']['FROZEN']
    games = deepcopy(arm['game_summaries'])
    for episode, game in enumerate(games):
        game['seed'] = audit.evaluation_seed(0, episode)
    audit.check_evaluation(games, 0, arm['evaluation_counts'])
    games[0]['seed'] = 291900000000
    with pytest.raises(ValueError, match='registered independent paired evaluation seeds'):
        audit.check_evaluation(games, 0, arm['evaluation_counts'])


def split_fixture(retained):
    life = deepcopy(retained['by_lifecycle'][0])
    ds = life['dataset']
    costs = ds['costs']
    costs['full_B_raw_tiles'] = costs.pop('full_A_raw_tiles')
    costs['full_B_acquisition_counts'] = costs.pop('full_A_acquisition_counts')
    games = [{k:v for k,v in game.items() if k!='split'} for game in ds['games']]
    # This ledger check needs score membership, not reconstructed boards/targets.
    scores = {g['episode']:[g['score']]+[0]*(g['steps']-1) for g in games}
    fit_last = games[ds['fit_game_count']-1]['episode']
    memories = {fit_last:audit.learned(ds['fit_memory'])}
    warm_raw = life['acquisition']['warmup']['raw_tiles']
    return ds, games, scores, memories, warm_raw, life['acquisition']['training']


def test_fit_prefix_cannot_include_heldout_observations(retained):
    args = split_fixture(retained)
    audit.check_split(*args)
    args[0]['fit_memory']['observations_seen'] += 64
    with pytest.raises(ValueError, match='heldout/future leaked into fit-prefix belief'):
        audit.check_split(*args)


def test_paid_unfinished_tail_cannot_disappear(retained):
    args = split_fixture(retained)
    audit.check_split(*args)
    args[0]['costs']['excluded_tail_raw_tiles'] = 0
    with pytest.raises(ValueError, match='paid full acquisition/excluded tail ledger'):
        audit.check_split(*args)


def accounting_fixture(retained):
    data = deepcopy(retained)
    account = data['accounting']
    account['new_actor_B_raw_tiles'] = account.pop('new_actor_A_raw_tiles')
    account['new_actor_B_counts'] = account.pop('new_actor_A_counts')
    account['development_reference'].update(previous_pilot='V291',
        previous_target_acquisition_raw_tiles=retained['accounting']['new_training_environment_observations'],
        previous_evaluation_counts=retained['accounting']['evaluation_counts'])
    return data


def test_previous_target_histories_are_not_new_source_inputs(retained):
    data = accounting_fixture(retained)
    processed = data['accounting']['processed_training_samples']
    audit.check_accounting(data, retained, processed)
    data['accounting']['inherited_costs_per_arm']['EPISODE_MEAN_MC']['old_A_target_raw'] = 131072
    with pytest.raises(ValueError, match='source once/new target full economic cost'):
        audit.check_accounting(data, retained, processed)


def test_raw_training_cost_cannot_be_replaced_by_processed_fit_samples(retained):
    data = accounting_fixture(retained)
    data['accounting']['new_actor_B_raw_tiles'] = data['accounting']['processed_training_samples']['EPISODE_MEAN_MC']
    with pytest.raises(ValueError, match='fresh physical acquisition/sample budget'):
        audit.check_accounting(data, retained, data['accounting']['processed_training_samples'])


def test_b_learning_requires_independent_utility_even_when_mse_improves(retained):
    summary = deepcopy(retained['summary'])
    records = summary['by_lifecycle']
    summary['bootstrap_seed'] = 29800001
    primary = summary['paired_contrasts']['EPISODE_MEAN_MC_minus_FROZEN']
    values = list(primary['lifecycle_deltas'].values())
    primary['ci95'] = [mean(min(values[p::4]) for p in range(4)),
        mean(max(values[p::4]) for p in range(4))]
    assert primary['ci95'][0] <= 0 and summary['independent_prediction_supported']
    summary['independent_learning_confirmed'] = summary['stable_b_learning_supported'] = False
    summary['independent_learning_status'] = 'NOT_SUPPORTED_CONDITIONAL_ON_FOUR_FROZEN_PARENTS'
    audit.check_result_summary(summary, records, 0)
    summary['stable_b_learning_supported'] = True
    with pytest.raises(ValueError, match='prediction substituted for independent complete-game gain'):
        audit.check_result_summary(summary, records, 0)


def test_adverse_fresh_life_cannot_be_dropped(retained):
    saved = deepcopy(retained['summary']['paired_contrasts']['EPISODE_MEAN_MC_minus_FROZEN'])
    values = list(saved['lifecycle_deltas'].values())
    audit.check_contrast(saved, values, 'higher_is_better')
    assert saved['adverse_lifecycles']
    saved['adverse_lifecycles'].pop()
    with pytest.raises(ValueError, match='signed adverse fresh histories'):
        audit.check_contrast(saved, values, 'higher_is_better')
