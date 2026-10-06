"""Frozen V305 statistics, noncommitting probes and confirmed novelty."""
from copy import deepcopy
from math import exp, log

import pytest

from acfqp.science.confirmed_context_v309 import ConfirmedContexts, MAX_DETECTION_RAW, NEW_POSTERIOR
from acfqp.science.observed_context_v305 import ObservedContexts


def memory(n, k):
    return dict(observations_seen=n, modules=[dict(id=0, alpha=k+1, beta=n-k+1)],
        pending=dict(n=0, fours=0))


def commit(router, n, k):
    payload = memory(n, k)
    return router.commit(payload, router.probe(payload))


def test_first_context_and_frozen_beta_scores_match_v305_exactly():
    router, old = ConfirmedContexts(), ObservedContexts()
    first = commit(router, 100, 10)
    old.observe(memory(100, 10))
    probed = router.probe(memory(100, 12))
    expected = old.observe(memory(100, 12))
    assert first['decision'] == 'FIRST_CONTEXT' and first['scores'] == []
    assert first['novelty_log_odds'] is first['novelty_posterior'] is None
    assert probed['scores'] == expected['scores']
    assert probed['decision'] == 'REUSE'
    assert not probed['prototype_committed']
    assert router.counts['log_beta_evaluations'] == 3 and router.counts['lgamma_evaluations'] == 9
    assert NEW_POSTERIOR == .99 and MAX_DETECTION_RAW == 4096


@pytest.mark.parametrize('final_k,decision', [(65, 'REUSE'), (105, 'CONFIRMED_NEW')])
def test_ambiguity_resolves_from_full_pool_and_commits_only_once(final_k, decision):
    router = ConfirmedContexts()
    commit(router, 10000, 1000)
    before = deepcopy(router.banks)
    pending = router.probe(memory(300, 45))
    assert pending['decision'] == 'PENDING_CONFIRMATION'
    assert 0. < pending['novelty_log_odds'] < log(99.)
    assert router.banks == before and router.counts['prototype_commits'] == 1
    with pytest.raises(ValueError, match='Pending confirmation'):
        router.commit(memory(300, 45), pending)
    final_payload = memory(600, final_k)
    resolved = router.probe(final_payload)
    assert resolved['decision'] == decision and router.banks == before
    route = router.commit(final_payload, resolved)
    assert route['statistics'] == dict(observations=600, fours=final_k)
    assert route['prototype_committed'] and router.counts['prototype_commits'] == 2
    if decision == 'REUSE':
        assert router.banks == [dict(context_id=0, observations=10600, fours=1000+final_k, visits=2)]
    else:
        assert router.banks[0] == before[0]
        assert router.banks[1] == dict(context_id=1, observations=600, fours=final_k, visits=1)


def test_novelty_odds_use_equal_prior_mass_and_uniform_known_contexts():
    router = ConfirmedContexts()
    commit(router, 10000, 1000)
    assert commit(router, 10000, 5000)['decision'] == 'CONFIRMED_NEW'
    probe = router.probe(memory(300, 90))
    scores = [row['log_bayes_factor'] for row in probe['scores']]
    assert probe['novelty_log_odds'] == pytest.approx(-log(sum(exp(bf) for bf in scores)/2))
    assert probe['novelty_posterior'] == pytest.approx(1./(1.+exp(-probe['novelty_log_odds'])))
    assert probe['decision'] == 'CONFIRMED_NEW'


def test_all_modules_and_pending_ranks_enter_probe_and_cap_does_not_contaminate_bank():
    router = ConfirmedContexts()
    commit(router, 10000, 1000)
    payload = dict(observations_seen=4200,
        modules=[dict(id=0, alpha=301, beta=2201), dict(id=1, alpha=201, beta=1401)],
        pending=dict(n=100, fours=5))
    # 2500 + 1600 committed ranks and 100 pending; none can be omitted.
    before = deepcopy(router.banks)
    probed = router.probe(payload)
    assert probed['statistics'] == dict(observations=4200, fours=505)
    assert probed['decision'] == 'PENDING_CONFIRMATION'
    capped = router.commit(payload, dict(probed, decision='CAP_REUSE_UNRESOLVED'))
    assert capped['decision'] == 'CAP_REUSE_UNRESOLVED'
    assert not capped['created'] and not capped['prototype_committed']
    assert capped['prototype_before'] == capped['prototype_after'] == before[0]
    assert router.banks == before and router.counts['prototype_commits'] == 1
    assert router.counts['cap_reuse_unresolved_calls'] == 1


def test_select_remains_readonly_best_known_even_for_new_distribution():
    router = ConfirmedContexts()
    commit(router, 10000, 1000)
    commit(router, 10000, 5000)
    before = deepcopy(router.banks)
    selected = router.select(memory(10000, 9000))
    assert selected['context_id'] == 1 and max(row['log_bayes_factor'] for row in selected['scores']) < 0.
    assert router.banks == before and router.counts['prototype_commits'] == 2


def test_missing_factual_statistics_fail_before_routing():
    payload = memory(300, 30)
    payload['observations_seen'] += 1
    with pytest.raises(ValueError, match='factual FIT prefix'):
        ConfirmedContexts().probe(payload)
