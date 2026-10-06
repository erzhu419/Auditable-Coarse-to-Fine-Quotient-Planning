"""Member probes and reachable continuation-threshold acquisition."""
from fractions import Fraction
from . import online_lifecycle_v206 as previous
from . import conditioned_mechanisms_v205 as policies

OPERATORS, ALPHABETS, FIELDS = previous.OPERATORS, previous.ALPHABETS, previous.FIELDS
BATCH, BUDGET, BETA = previous.BATCH, previous.BUDGET, previous.BETA
empty, fit, update, make_plan = previous.empty, previous.fit, previous.update, previous.make_plan

def choose(model, case, current, work):
    work['acquisition_choice_calls'] += 1
    members = {op: current['envelopes'][op]['n'] for op in OPERATORS}
    for op in OPERATORS:
        if members[op] == 0:
            work['member_pilot_choices'] += 1
            return dict(operator=op,pilot=True,reason='member_probe',policy=None,
                policy_scores=None,projection_counts=members,decision_evidence=None)
    queries = policies.query_decisions(model,case,work)
    lo,hi = current['envelopes']['RECOVERY_RETRY']['bounds']['DELIVERY']
    cost = Fraction(case['retry_cost'])
    thresholds = {'goal':cost/4,'risk':(4+cost)/8}
    evidence = {query:dict(root=queries[query]['policy']['START',4],
                threshold=threshold,lower=lo,upper=hi,
                unresolved=queries[query]['policy']['START',4]=='DETOUR' and lo<=threshold<=hi)
                for query,threshold in thresholds.items()}
    if any(row['unresolved'] for row in evidence.values()):
        work['continuation_choices'] += 1
        return dict(operator='RECOVERY_RETRY',pilot=False,reason='continuation',policy=None,
            policy_scores=None,projection_counts=members,decision_evidence=evidence)
    point = previous.robust.cold_policy(model,case,current,work)
    work['ratio_choices'] += 1
    return dict(operator=point['operator'],pilot=False,reason='ratio',policy=point['policy'],
        policy_scores=point['policy_scores'],projection_counts=members,decision_evidence=evidence)
