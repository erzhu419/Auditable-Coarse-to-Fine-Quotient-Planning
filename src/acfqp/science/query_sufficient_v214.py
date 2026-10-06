"""Query-ready candidate sets; risk bounds remain the full V213 joint boxes."""
from fractions import Fraction as F
from . import latent_mechanisms_v213 as prior
OPERATORS, ALPHABETS = prior.OPERATORS, prior.ALPHABETS
empty, vectors, queries = prior.empty, prior.vectors, prior.queries
THRESHOLD = F(1,20)
WEIGHTS = {'reward':(1,0,0), 'goal':(1,0,4), 'risk':(1,4,4)}

def query_proxy(member, anchors, case, plan, work):
    if not plan['candidates']: return None
    chosen=queries(plan); regrets=[]
    for i in plan['candidates']:
        combined={op:{cat:member[op][cat]+anchors[i][op][cat] for cat in ALPHABETS[op]} for op in OPERATORS}
        pure=vectors(case,prior.posterior(combined));values=[]
        for q,w in WEIGHTS.items():
            value=lambda v:v[0]*w[0]-v[1]*w[1]+v[2]*w[2]
            values.append(max(value(v) for v in pure.values())-value(pure[chosen[q]['policy']]))
            work['query_proxy_policy_comparisons']+=len(pure)
        regrets.append(sum(values)/3)
    return max(regrets)

def make_plan(member, anchors, case, arm, work, identity=None, force_member=False):
    result=prior.make_plan(member,anchors,case,arm,work,identity,force_member)
    result['query_proxy']=query_proxy(member,anchors,case,result,work)
    result['query_ready']=(result['mode']=='library' and result['utility_lower']>=2
                           and result['query_proxy'] is not None and result['query_proxy']<=THRESHOLD)
    return result

def choose(member, anchors, case, arm, plan, spent, work, source=False):
    if arm=='SET' and not source and plan['query_ready']: return None
    return prior.choose(member,anchors,case,'LATENT' if arm in ('SET','STRICT') else arm,
                        plan,spent,work,source)
