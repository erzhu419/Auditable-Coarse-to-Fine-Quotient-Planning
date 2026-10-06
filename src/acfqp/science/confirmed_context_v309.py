"""Paid observed-context probes, with fixed evidence required for novelty."""
from math import exp, log
from time import process_time

from .observed_context_v305 import ObservedContexts

NEW_POSTERIOR = .99
NEW_LOG_ODDS = log(99.)
MAX_DETECTION_RAW = 4096


class ConfirmedContexts(ObservedContexts):
    def probe(self, memory):
        """Use all factual ranks without changing any stored prototype."""
        started = process_time()
        stats, scores = self._statistics(memory), None
        scores = self._scores(stats)
        best = max(scores, key=lambda row: (row['log_bayes_factor'], -row['context_id'])) if scores else None
        if best is None:
            decision, odds, posterior = 'FIRST_CONTEXT', None, None
        else:
            largest = best['log_bayes_factor']
            odds = -(largest + log(sum(exp(row['log_bayes_factor']-largest) for row in scores)/len(scores)))
            posterior = 1./(1.+exp(-odds)) if odds >= 0. else exp(odds)/(1.+exp(odds))
            decision = ('REUSE' if largest >= 0. else
                'CONFIRMED_NEW' if odds >= NEW_LOG_ODDS else 'PENDING_CONFIRMATION')
            self.counts.update(novelty_odds_evaluations=1, novelty_posterior_evaluations=1)
        created = decision in ('FIRST_CONTEXT', 'CONFIRMED_NEW')
        context_id = len(self.banks) if created else best['context_id']
        before = None if created else dict(self.banks[context_id])
        self.counts['probe_calls'] += 1
        self.counts['pending_confirmation_probes'] += decision == 'PENDING_CONFIRMATION'
        result = dict(statistics=stats, scores=scores, context_id=context_id, created=created,
            prototype_before=before, prototype_after=None if created else dict(before),
            prototype_committed=False, decision=decision,
            novelty_log_odds=odds, novelty_posterior=posterior)
        self.cpu_seconds += process_time()-started
        return result

    def commit(self, memory, decision):
        """Commit one resolved detector pool; an unresolved cap preserves banks."""
        if decision['decision'] == 'PENDING_CONFIRMATION':
            raise ValueError('Pending confirmation cannot commit a context prototype')
        if decision['decision'] not in ('FIRST_CONTEXT', 'REUSE', 'CONFIRMED_NEW', 'CAP_REUSE_UNRESOLVED'):
            raise ValueError('Unknown confirmed-context decision')
        started = process_time()
        stats = self._statistics(memory)
        self.counts['commit_calls'] += 1
        result = dict(decision, statistics=stats)
        if decision['decision'] == 'CAP_REUSE_UNRESOLVED':
            bank = self.banks[decision['context_id']]
            result.update(created=False, prototype_before=dict(bank), prototype_after=dict(bank),
                prototype_committed=False)
            self.counts['cap_reuse_unresolved_calls'] += 1
        else:
            if decision['created']:
                bank = dict(context_id=len(self.banks), observations=0, fours=0, visits=0)
                self.banks.append(bank)
                before = None
                self.counts['context_creations'] += 1
            else:
                bank = self.banks[decision['context_id']]
                before = dict(bank)
            bank['observations'] += stats['observations']
            bank['fours'] += stats['fours']
            bank['visits'] += 1
            self.counts['prototype_commits'] += 1
            result.update(context_id=bank['context_id'], prototype_before=before,
                prototype_after=dict(bank), prototype_committed=True)
        self.cpu_seconds += process_time()-started
        return result
