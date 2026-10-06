"""Task-sufficient constrained evidence targeting, with real member certificates."""
from copy import deepcopy
from fractions import Fraction
from . import online_lifecycle_v206 as previous
OPERATORS, ALPHABETS, FIELDS = previous.OPERATORS, previous.ALPHABETS, previous.FIELDS
BATCH, BUDGET, BETA = previous.BATCH, previous.BUDGET, previous.BETA
empty, fit, update, make_plan = previous.empty, previous.fit, previous.update, previous.make_plan
DELTA=Fraction(1,20)

def point_scores(current):
    return {name:max(Fraction(0),v[0]+4*v[2])*min(Fraction(1),DELTA/v[1])
            for name,v in current['pure_vectors'].items() if name!='WAIT'}

def choose(model, case, current, work):
    work['acquisition_choice_calls']+=1
    members={op:current['envelopes'][op]['n'] for op in OPERATORS}
    for op in OPERATORS:
        if members[op]==0:
            work['member_pilot_choices']+=1
            return dict(operator=op,pilot=True,reason='member_probe',policy=None,
                        policy_scores=None,projection_counts=members,sensitivity_scores=None)
    scores=point_scores(current)
    capable=[name for name,value in scores.items() if value>=2]
    policy=min(capable,key=lambda name:(2 if name=='DETOUR_RETRY' else 1,-scores[name],name)) if capable else min(scores,key=lambda name:(-scores[name],name))
    sensitivity=None
    if policy=='SHORT':
        op='SHORT_PASS'
    elif policy=='DETOUR_RETURN':
        op='DETOUR_PASS'
    else:
        sensitivity={}
        for candidate in ('DETOUR_PASS','RECOVERY_RETRY'):
            box=deepcopy(current['envelopes'])
            probabilities=previous.learner.probabilities(model,case,candidate,work)
            box[candidate]['bounds']={cat:[p,p] for cat,p in probabilities.items()}
            upper=previous.robust.risk_bounds(box,work)[policy]
            lower=previous.robust.goals_lower(box,case,work)[policy]
            weight=Fraction(1) if upper<=DELTA else DELTA/upper
            sensitivity[candidate]=max(Fraction(0),weight*lower)
            work['sensitivity_candidates']+=1
        op=min(sensitivity,key=lambda name:(-sensitivity[name],OPERATORS.index(name)))
    work['task_target_choices']+=1
    return dict(operator=op,pilot=False,reason='constrained_target',policy=policy,
                policy_scores=scores,projection_counts=members,sensitivity_scores=sensitivity)
