"""Persistent Bernoulli contexts learned from observed spawn sufficient statistics."""
from collections import Counter
from math import lgamma
from time import process_time


class ObservedContexts:
    def __init__(self):
        self.banks=[]
        self.counts=Counter()
        self.cpu_seconds=0.

    def _statistics(self,memory):
        modules=memory['modules']; pending=memory['pending']
        n,k=pending['n'],pending['fours']
        for module in modules:
            alpha,beta=module['alpha'],module['beta']
            n+=alpha+beta-2; k+=alpha-1
        if n!=memory['observations_seen'] or not 0<=k<=n:
            raise ValueError('Observed context statistics do not cover the factual FIT prefix')
        self.counts.update(statistics_module_visits=len(modules),statistics_pending_reads=2,
            statistics_parameter_reads=2*len(modules),statistics_extractions=1)
        return dict(observations=n,fours=k)

    def _beta(self,k,n):
        self.counts.update(log_beta_evaluations=1,lgamma_evaluations=3)
        return lgamma(1+k)+lgamma(1+n-k)-lgamma(2+n)

    def _scores(self,stats):
        scores=[]; n,k=stats['observations'],stats['fours']
        for bank in self.banks:
            old_n,old_k=bank['observations'],bank['fours']
            score=self._beta(old_k+k,old_n+n)-self._beta(old_k,old_n)-self._beta(k,n)
            scores.append(dict(context_id=bank['context_id'],log_bayes_factor=score))
        self.counts.update(candidate_scores=len(scores),score_comparisons=max(0,len(scores)-1))
        return scores

    def observe(self,memory):
        started=process_time(); stats=self._statistics(memory); scores=self._scores(stats)
        best=max(scores,key=lambda r:(r['log_bayes_factor'],-r['context_id'])) if scores else None
        created=best is None or best['log_bayes_factor']<0.
        if created:
            bank=dict(context_id=len(self.banks),observations=0,fours=0,visits=0)
            self.banks.append(bank); before=None
            self.counts['context_creations']+=1
        else:
            bank=self.banks[best['context_id']]; before=dict(bank)
        bank['observations']+=stats['observations']; bank['fours']+=stats['fours']; bank['visits']+=1
        self.counts.update(observe_calls=1,prototype_commits=1)
        result=dict(statistics=stats,scores=scores,context_id=bank['context_id'],created=created,
            prototype_before=before,prototype_after=dict(bank))
        self.cpu_seconds+=process_time()-started
        return result

    def select(self,memory):
        """Classify among stored contexts without committing any observations."""
        started=process_time(); stats=self._statistics(memory); scores=self._scores(stats)
        best=max(scores,key=lambda r:(r['log_bayes_factor'],-r['context_id']))
        self.counts['select_calls']+=1
        result=dict(statistics=stats,scores=scores,context_id=best['context_id'])
        self.cpu_seconds+=process_time()-started
        return result
