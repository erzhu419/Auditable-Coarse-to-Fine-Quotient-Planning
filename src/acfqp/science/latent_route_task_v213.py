"""Simulator-only finite recurring kernels; public cases contain no identity."""
from copy import deepcopy
import random
from . import mechanism_switch_task_v205 as truth

def world(life):
    labels=list(truth.WEATHER);random.Random(214900+life).shuffle(labels)
    targets=list(truth.WEATHER)*8;random.Random(215000+life).shuffle(targets)
    costs=[(op,retry) for op in truth.OPERATING for retry in truth.RETRY_COSTS]*6
    random.Random(215100+life).shuffle(costs)
    cases=[dict(id=f'unit_{i:02d}',operating='high',retry_cost='19/20') for i in range(3)]
    cases += [dict(id=f'unit_{i+3:02d}',operating=op,retry_cost=retry) for i,(op,retry) in enumerate(costs)]
    kernels=[truth.laws(dict(weather=label)) for label in labels+targets]
    identities=[0,1,2]+[labels.index(label) for label in targets]
    return cases,kernels,identities
