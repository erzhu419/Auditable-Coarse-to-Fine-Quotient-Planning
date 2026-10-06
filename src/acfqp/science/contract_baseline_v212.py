"""Direct contract-aware sufficient-count baseline against frozen V210 learner."""
from copy import deepcopy
from . import strategic_maintenance_v210 as prior
OPERATORS, ALPHABETS, FIELDS = prior.OPERATORS, prior.ALPHABETS, prior.FIELDS
empty, update, make_plan = prior.empty, prior.update, prior.make_plan

def fit(model, arm, work):
    if arm != 'DIRECT': return prior.fit(model,arm,work)
    result=deepcopy(model);work['online_fit_calls']+=1
    for op in OPERATORS:
        result['selected_fields'][op]=['weather']
        result['scores'][op]=[]
        work['condition_operator_fits']+=1
    result['certificate_fields']=['weather']
    return result

def next_choice(model, case, plan, arm, spent, work):
    if arm == 'DIRECT':
        return None if spent==384 or plan['utility_lower']>=2 else prior.prior.choose(model,case,plan,work)
    return prior.next_choice(model,case,plan,arm,spent,work)
