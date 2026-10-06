"""Unknown finite-library applicability from observed action consequences."""
from fractions import Fraction as F
from copy import deepcopy
from math import ceil, floor, log
from itertools import combinations
from . import strategic_maintenance_v210 as settled
from . import constrained_acquisition_v208 as acquisition
robust=settled.robust
OPERATORS,ALPHABETS=settled.OPERATORS,settled.ALPHABETS
BETA=log(2*5544/.05)

def empty():return {op:dict.fromkeys(ALPHABETS[op],0) for op in OPERATORS}

def interval(k,n,work):
    work['interval_calls']+=1
    if not n:return F(0),F(1)
    x=k/n
    if k:
        lo,hi=0.,x
        for _ in range(64):
            mid=(lo+hi)/2
            if n*robust.confidence._kl(x,mid,work)>BETA:lo=mid
            else:hi=mid
        lower=lo
    else:lower=0.
    if k<n:
        lo,hi=x,1.
        for _ in range(64):
            mid=(lo+hi)/2
            if n*robust.confidence._kl(x,mid,work)>BETA:hi=mid
            else:lo=mid
        upper=hi
    else:upper=1.
    return F(floor(lower*robust.GRID),robust.GRID),F(ceil(upper*robust.GRID),robust.GRID)

def boxes(counts,work):
    return {op:dict(n=sum(row.values()),counts=deepcopy(row),
             bounds={cat:list(interval(k,sum(row.values()),work)) for cat,k in row.items()})
            for op,row in counts.items()}

def posterior(counts):
    return {op:{cat:F(2*k+1,2*sum(row.values())+len(row)) for cat,k in row.items()} for op,row in counts.items()}

def vectors(case,p):
    sc,dc=robust.learning.COST_PRIOR[case['operating']];rc=F(case['retry_cost'])
    s,d,q=(p[op] for op in OPERATORS);rec=d['RECOVERY']
    return {'WAIT':[F(0)]*3,'SHORT':[-sc,s['LOST'],s['DELIVERY']],
            'DETOUR_RETURN':[-dc,d['LOST'],d['DELIVERY']],
            'DETOUR_RETRY':[-dc-rec*rc,d['LOST']+rec*q['LOST'],d['DELIVERY']+rec*q['DELIVERY']]}

def make_plan(member,anchors,case,arm,work,identity=None,force_member=False):
    raw=boxes(member,work);blocks={};candidates=[]
    if anchors and arm!='LOCAL' and not force_member:
        for i,anchor in enumerate(anchors):
            if arm=='ORACLE' and i!=identity:continue
            source=boxes(anchor,work);block=deepcopy(raw);ok=True
            for op in OPERATORS:
                for cat in ALPHABETS[op]:
                    a,b=raw[op]['bounds'][cat],source[op]['bounds'][cat]
                    pair=[max(a[0],b[0]),min(a[1],b[1])]
                    if pair[0]>pair[1]:ok=False
                    block[op]['bounds'][cat]=pair
            if ok:candidates.append(i);blocks[i]=block
    if candidates:
        risks={};goals={}
        for i,block in blocks.items():
            r=robust.risk_bounds(block,work);g=robust.goals_lower(block,case,work)
            for policy in r:
                risks[policy]=max(risks.get(policy,F(0)),r[policy])
                goals[policy]=min(goals.get(policy,g[policy]),g[policy])
        means=[]
        for i in candidates:
            combined={op:{cat:member[op][cat]+anchors[i][op][cat] for cat in ALPHABETS[op]} for op in OPERATORS}
            means.append(posterior(combined))
        p={op:{cat:sum(row[op][cat] for row in means)/len(means) for cat in ALPHABETS[op]} for op in OPERATORS}
        envelope=deepcopy(raw)
        for op in OPERATORS:
            for cat in ALPHABETS[op]:
                envelope[op]['bounds'][cat]=[min(block[op]['bounds'][cat][0] for block in blocks.values()),
                                            max(block[op]['bounds'][cat][1] for block in blocks.values())]
        mode='library'
    else:
        envelope=raw;risks=robust.risk_bounds(raw,work);goals=robust.goals_lower(raw,case,work)
        p=posterior(member);mode='member'
    pure=vectors(case,p);work['planning_calls']+=1
    return dict(**robust.solve(pure,risks,goals,work),envelopes=envelope,risks=risks,
                goals_lower=goals,pure_vectors=pure,candidates=candidates,
                candidate_envelopes=blocks,mode=mode)

def choose(member,anchors,case,arm,plan,spent,work,source=False):
    if source and arm!='LOCAL':
        return None if spent==1152 else dict(operator=OPERATORS[(spent//16)%3],reason='paid_anchor')
    cap=1152 if source else 384
    if spent==cap:return None
    if plan['utility_lower']>=2 and (arm=='LOCAL' or source or len(plan['candidates'])==1):return None
    if arm=='LATENT' and len(plan['candidates'])>1:
        means={i:posterior(anchors[i]) for i in plan['candidates']};scores={}
        for op in OPERATORS:
            scores[op]=min(sum(abs(means[a][op][cat]-means[b][op][cat]) for cat in ALPHABETS[op])/2
                           for a,b in combinations(plan['candidates'],2))
        op=min(OPERATORS,key=lambda x:(-scores[x],OPERATORS.index(x)))
        return dict(operator=op,reason='identify',scores=scores)
    # LOCAL and unresolved member fallback use the frozen V208 acquisition.
    model=dict(tables={op:[] for op in OPERATORS},selected_fields={op:[] for op in OPERATORS})
    # V208 sensitivity uses empirical means; expose only this member's observed counts.
    context=dict(case,weather='member')
    for op in OPERATORS:model['tables'][op]=[dict(context=context,counts=member[op])]
    choice=acquisition.choose(model,context,plan,work)
    return dict(operator=choice['operator'],reason='certify',detail=choice)

def queries(plan):
    weights={'reward':(1,0,0),'goal':(1,0,4),'risk':(1,4,4)}
    result={}
    for q,w in weights.items():
        value=lambda name: (plan['pure_vectors'][name][0]*w[0]-plan['pure_vectors'][name][1]*w[1]+plan['pure_vectors'][name][2]*w[2])
        result[q]=dict(policy=min(plan['pure_vectors'],key=lambda name:(-value(name),name)))
    return result
