"""Observed evidence routing, sufficient-statistic completeness and readonly reuse."""
from copy import deepcopy
from math import lgamma
import pytest

from acfqp.science.observed_context_v305 import ObservedContexts


def memory(n,k):
    return dict(observations_seen=n,modules=[dict(id=0,alpha=k+1,beta=n-k+1)],pending=dict(n=0,fours=0))


def test_distinct_observations_create_and_return_reuses_without_task_labels():
    router=ObservedContexts(); a=router.observe(memory(10000,1000)); b=router.observe(memory(10000,5000))
    returned=router.observe(memory(10000,1010))
    assert [a['context_id'],b['context_id'],returned['context_id']]==[0,1,0]
    assert [a['created'],b['created'],returned['created']]==[True,True,False]
    assert router.banks==[dict(context_id=0,observations=20000,fours=2010,visits=2),
        dict(context_id=1,observations=10000,fours=5000,visits=1)]
    assert returned['prototype_before']==a['prototype_after']
    assert router.counts['context_creations']==2 and router.counts['prototype_commits']==3


def test_all_modules_and_uncommitted_pending_observations_enter_context():
    router=ObservedContexts()
    payload=dict(observations_seen=100,active_module_id=1,
        modules=[dict(id=0,alpha=11,beta=61),dict(id=1,alpha=11,beta=11)],pending=dict(n=10,fours=5))
    result=router.observe(payload)
    assert result['statistics']==dict(observations=100,fours=25)
    assert router.counts['statistics_module_visits']==2 and router.counts['statistics_parameter_reads']==4


def test_select_preserves_prototypes_and_uses_observation_evidence():
    router=ObservedContexts(); router.observe(memory(10000,1000)); router.observe(memory(10000,5000))
    before=deepcopy(router.banks)
    assert router.select(memory(10000,1000))['context_id']==0
    assert router.select(memory(10000,5000))['context_id']==1
    assert router.banks==before and router.counts['prototype_commits']==2 and router.counts['select_calls']==2


def test_same_distribution_bayes_factor_is_the_frozen_beta_integral():
    router=ObservedContexts(); router.observe(memory(100,10)); result=router.observe(memory(100,12))
    def beta(k,n): return lgamma(k+1)+lgamma(n-k+1)-lgamma(n+2)
    assert result['scores'][0]['log_bayes_factor']==beta(22,200)-beta(10,100)-beta(12,100)
    assert router.counts['log_beta_evaluations']==3 and router.counts['lgamma_evaluations']==9


def test_factual_statistic_mismatch_cannot_route():
    payload=memory(100,10);payload['observations_seen']=101
    with pytest.raises(ValueError,match='factual FIT prefix'): ObservedContexts().observe(payload)
