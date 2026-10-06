"""Fixed-index selection and paired independent-batch scientific accounting."""
from copy import deepcopy
import pytest

from acfqp.science import natural_continuation_analysis_v285 as core


def cohort(validation=None):
    states, rollouts = [], []
    parents = {life: life % 4 for life in range(16)}
    for life in parents:
        for phase in core.PHASES:
            for group in core.GROUPS:
                for slot in range(4):
                    state_id = f'{life}/{phase}/{group}/{slot}'
                    state = dict(state_id=state_id, lifecycle=life, phase=phase,
                        group=group, legal_actions=['UP', 'RIGHT', 'LEFT'],
                        proxy_action='LEFT', short_action='UP', retained_action='RIGHT', slot=slot)
                    states.append(state)
                    for batch in ('discovery', 'validation'):
                        for action in state['legal_actions']:
                            for replica in range(2):
                                value = {'LEFT': 0., 'RIGHT': 5., 'UP': 4.}[action]
                                if batch == 'validation':
                                    value = (validation(state, action, replica) if validation else
                                        {'LEFT': (0., 0.), 'RIGHT': (-3., -1.), 'UP': (-2., -2.)}[action][replica])
                                rollouts.append(dict(state_id=state_id, action=action, batch=batch,
                                    replica_index=replica, total_utility=value,
                                    suffix_utility=-value, first_score=4096))
    return states, rollouts, parents


def test_selection_uses_indices_and_tail_competition_only():
    selected = core.select_indices(25, [24, 0, 23, 1, 2, 6, 7, 8, 12, 13, 18, 19])
    assert selected == dict(uniform=(0, 6, 12, 18), competition=(1, 7, 13, 23))
    assert not set(selected['uniform']) & set(selected['competition'])
    # Candidate order and hypothetical outcomes cannot affect the same index set.
    rows = [dict(decision=i, future_utility=(-1)**i*i) for i in [24, 23, 19, 13, 8, 7, 2, 1]]
    assert core.select_indices(25, [row['decision'] for row in rows]) == selected
    for row in rows:
        row['future_utility'] *= -1000
    assert core.select_indices(25, [row['decision'] for row in rows]) == selected
    with pytest.raises(ValueError, match='four distinct'):
        core.select_indices(25, [0, 6, 12, 18, 1, 2, 3])


def test_discovery_selects_total_utility_and_validation_keeps_negative_gains():
    states, rollouts, parents = cohort()
    result = core.summarize(states, rollouts, parents, replicas=2, draws=4)
    state = result['state_results'][0]
    assert state['winner'] == 'RIGHT'
    assert state['discovery_means'] == dict(LEFT=0., RIGHT=5., UP=4.)
    assert state['validation_means'] == dict(LEFT=0., RIGHT=-2., UP=-2.)
    assert state['contrasts']['winner_minus_proxy'] == dict(mean=-2., paired_mc_se=1.)
    assert state['contrasts']['short_minus_proxy'] == dict(mean=-2., paired_mc_se=0.)
    for group in result['groups'].values():
        for contrast in group['contrasts'].values():
            assert contrast['mean'] == -2. and contrast['ci95'] == [-2., -2.]
            assert contrast['improved_equal_worse'] == [0, 0, 16]
            assert contrast['adverse_lifecycles'] == list(range(16))


def test_validation_cannot_reselect_winner_and_discovery_uses_lexical_ties():
    states, rollouts, parents = cohort(lambda state, action, replica:
        dict(LEFT=30., RIGHT=0., UP=100.)[action])
    result = core.summarize(states, rollouts, parents, replicas=2, draws=2)
    state = result['state_results'][0]
    assert state['winner'] == 'RIGHT'  # validation's UP is not an argmax selector
    assert state['contrasts']['winner_minus_proxy']['mean'] == -30.
    assert state['contrasts']['short_minus_proxy']['mean'] == 70.
    tied = deepcopy(rollouts)
    for row in tied:
        if row['batch'] == 'discovery':
            row['total_utility'] = 5.
    tied_result = core.summarize(states, tied, parents, replicas=2, draws=2)
    assert all(row['winner'] == 'LEFT' for row in tied_result['state_results'])


def test_groups_states_phases_and_lifecycles_have_declared_equal_weights():
    phase_value = dict(A=0., B=100., A_prime=1000.)
    def validation(state, action, replica):
        offset = 10000. if state['group'] == 'competition' else 0.
        gain = state['lifecycle']+phase_value[state['phase']]+state['slot']+offset
        return replica + (gain if action != 'LEFT' else 0.)
    states, rollouts, parents = cohort(validation)
    result = core.summarize(states, rollouts, parents, replicas=2, draws=2)
    for group_name, offset in [('uniform', 0.), ('competition', 10000.)]:
        group = result['groups'][group_name]
        contrast = group['contrasts']['winner_minus_proxy']
        assert contrast['mean'] == pytest.approx(7.5 + 1100./3. + 1.5 + offset)
        for life in group['by_lifecycle']:
            assert life['contrasts']['winner_minus_proxy'] == pytest.approx(
                life['lifecycle']+1100./3.+1.5+offset)
            for phase in core.PHASES:
                assert life['phases'][phase]['contrasts']['winner_minus_proxy'] == pytest.approx(
                    life['lifecycle']+phase_value[phase]+1.5+offset)
        assert len(contrast['lifecycle_deltas']) == 16
        assert group['states'] == 192


def test_bootstrap_resamples_whole_lifecycles_within_four_fixed_parents(monkeypatch):
    calls = []
    class FixedParentRng:
        def __init__(self, seed):
            assert seed == 28500001
        def choices(self, values, k):
            assert k == 4 and len(set(int(value) % 4 for value in values)) == 1
            calls.append(list(values))
            return [values[0]]*k
    monkeypatch.setattr(core.random, 'Random', FixedParentRng)
    records = [dict(lifecycle=i, parent=i % 4, contrasts=dict(winner_minus_proxy=float(i)))
               for i in range(16)]
    contrast = core._bootstrap(records, 'winner_minus_proxy', 3)
    assert len(calls) == 12
    assert contrast['mean'] == 7.5 and contrast['ci95'] == [1.5, 1.5]
    assert contrast['parent_mean_deltas'] == {'0': 6., '1': 7., '2': 8., '3': 9.}
    assert contrast['interval_scope'] == 'CONDITIONAL_ON_FOUR_FROZEN_PARENTS'


def test_missing_or_duplicate_replica_cannot_become_an_unpaired_contrast():
    states, rollouts, parents = cohort()
    with pytest.raises(ValueError, match='complete independent replica'):
        core.summarize(states, rollouts[1:], parents, replicas=2, draws=2)
    with pytest.raises(ValueError, match='duplicate continuation replica'):
        core.summarize(states, rollouts+[rollouts[0]], parents, replicas=2, draws=2)
    with pytest.raises(ValueError, match='exactly four states'):
        core.summarize(states[1:], [row for row in rollouts
            if row['state_id'] != states[0]['state_id']], parents, replicas=2, draws=2)
